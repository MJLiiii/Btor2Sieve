(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x4131 (bvor (bvlshr i_4 (bvurem (_ bv3 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv3 3) (_ bv3 3)))))))
 (let ((?x5849 (ite (and (distinct ?x4131 i_4) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x5849 (_ bv1 1))))))
(assert
 (let (($x174 (and (distinct i_4 (_ bv7 3)) true)))
(not $x174)))
(check-sat)
