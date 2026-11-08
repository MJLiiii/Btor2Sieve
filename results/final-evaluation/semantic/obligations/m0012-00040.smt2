(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x5195 ((_ extract 2 2) i_4)))
 (let ((?x133 ((_ extract 1 0) i_4)))
 (let ((?x1796 (concat ?x133 ?x5195)))
 (let ((?x1148 (bvor (bvshl i_4 (bvurem (_ bv1 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv1 3) (_ bv3 3)))))))
 (let ((?x25 (ite (and (distinct ?x1148 ?x1796) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x25 (_ bv1 1)))))))))
(assert
 (let (($x71 (= i_4 (_ bv2 3))))
(not $x71)))
(check-sat)
