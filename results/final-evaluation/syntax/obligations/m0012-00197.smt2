(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x63 (bvor (bvshl i_4 (bvurem (_ bv3 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv3 3) (_ bv3 3)))))))
 (let ((?x5237 (ite (and (distinct ?x63 i_4) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x5237 (_ bv1 1))))))
(assert
 (let (($x69 (= i_4 (_ bv7 3))))
(not $x69)))
(check-sat)
