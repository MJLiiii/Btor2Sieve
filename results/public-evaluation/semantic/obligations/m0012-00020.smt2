(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x1353 (bvor (bvshl i_4 (bvurem (_ bv0 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv0 3) (_ bv3 3)))))))
 (let ((?x39 (ite (and (distinct ?x1353 i_4) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x39 (_ bv1 1))))))
(assert
 (let ((?x1353 (bvor (bvshl i_4 (bvurem (_ bv0 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv0 3) (_ bv3 3)))))))
(let (($x325 (and (distinct ?x1353 (_ bv3 3)) true)))
(not $x325))))
(check-sat)
