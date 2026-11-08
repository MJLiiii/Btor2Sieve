(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x4991 (bvor (bvlshr i_4 (bvurem (_ bv3 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv3 3) (_ bv3 3)))))))
 (let ((?x1402 (ite (and (distinct ?x4991 i_4) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x1402 (_ bv1 1))))))
(assert
 (let (($x3268 (bvuge i_4 (_ bv4 3))))
(not $x3268)))
(check-sat)
