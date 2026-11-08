(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x168 (= i_2 (_ bv7 4))))
(not $x168)))
(check-sat)
