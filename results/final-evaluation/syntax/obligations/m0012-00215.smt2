(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x95 (bvor (bvlshr i_4 (bvurem (_ bv0 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv0 3) (_ bv3 3)))))))
 (let ((?x3465 (ite (and (distinct ?x95 i_4) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x3465 (_ bv1 1))))))
(assert
 (let (($x71 (= i_4 (_ bv4 3))))
(not $x71)))
(check-sat)
